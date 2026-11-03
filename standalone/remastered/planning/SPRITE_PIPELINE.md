# Sprite asset pipeline

Status: implemented and exported from the remastered game source. The pipeline preserves original sprite bytes and pixels. The original border glyph consumer is integrated; shared-engine animation compatibility is verified separately, as described below.

## Run it

From the repository root:

    python3 standalone/remastered/tools/export_sprite_assets.py
    python3 standalone/remastered/tools/check_sprite_assets.py --full --report standalone/remastered/tests/sprite-assets-checks.json

Python 3.10+ and Pillow are required. Pillow 11.3.0 was already installed and used for this run. No new dependencies were installed.

The exporter can also accept another source root, an entrypoint relative to that root, page size and transparent gutter:

    python3 standalone/remastered/tools/export_sprite_assets.py --source /path/to/game --dme "Cave Crawlers.dme" --output /path/to/generated/sprites --page-size 2048 --gutter 1

Use the same exporter and Pillow version when comparing PNG file hashes. The validation also compares decoded RGBA pixels independently of PNG compression.

## Files

| File | Purpose |
| --- | --- |
| [export_sprite_assets.py](/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/tools/export_sprite_assets.py) | Deterministic source discovery, metadata parsing, atlas export and roundtrip validation. |
| [check_sprite_assets.py](/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/tools/check_sprite_assets.py) | Focused fixtures and complete-game repeatability check. |
| [manifest.json](/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/assets/sprites/manifest.json) | Original resource paths/hashes, references, state metadata, frame rectangles, pages, notices and issues. |
| [atlas-000.png](/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/assets/sprites/atlas-000.png), [atlas-001.png](/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/assets/sprites/atlas-001.png), [atlas-002.png](/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/assets/sprites/atlas-002.png) | Original pixels packed into three 2048 × 2048 RGBA pages. |
| [validation.json](/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/assets/sprites/validation.json) | Exact full-sheet reconstruction results for this export. |
| [sprite-assets-checks.json](/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/tests/sprite-assets-checks.json) | Focused and full-source test evidence, tied to exporter/test script hashes. |
| [LICENSE](/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/assets/sprites/notices/LICENSE) and [README](/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/assets/sprites/notices/README) | Exact copies of notices from the source tree. Each asset links to them. |

The output directory is generated and replaceable. Edit source sprites in the game tree; then rebuild. The exporter rejects an output directory inside the source tree and refuses to replace a nonempty directory without its own manifest marker. It stages and validates the export before replacing its generated directory. An export with referenced missing/invalid resources still produces a diagnostic manifest, but exits with failure; do not ship it as a successful build.

## Current inventory

| Measure | Result |
| --- | ---: |
| DMI/PNG candidates in the game source tree | 164 |
| Files decoded and exported | 162 |
| Empty files quarantined and reported | 2 |
| State entries, including movement variants and duplicate occurrences | 1,712 |
| Direction/animation cells | 9,074 |
| Additional cells beyond declared states, retained for lossless reconstruction | 237 |
| Atlas pages | 3 |
| Blocking errors | 0 |
| Warnings describing existing source irregularities | 41 |

The three PNG pages total about 1.1 MB on disk; the readable JSON manifest is about 6.8 MB. Each page is 16 MiB decoded RGBA, so a mobile consumer should load needed pages and release unused ones. Nothing is resized, trimmed, rotated, blended, or recolored. Cells retain their native dimensions, including the 54 × 54 Pandora tapestry and normal 32 × 32 sprites.

Source discovery scans only the specified game tree, including nested Code/Items/Icons and Code/Building folders. It excludes backups, tests, generated assets, distributions, app bundles, version-control folders and the generated Interface/border-icons directory. It also follows the DME's included files and FILE_DIR search paths to record static resource references. 105 of the current assets have such references; remaining assets are retained rather than assumed unused. Macro-generated resource names and conditional compilation are not evaluated. Runtime-generated portrait names are recorded as informational entries, not mistaken for missing files.

## Manifest contract

1. Find an asset by its exact source path, for example Icons/Orc.dmi. Asset and state IDs are safe hash-based strings, independent of page packing.
2. Resolve a state using its name and movement value. An ordinary state and a movement state may legitimately share a name. The same name/movement pair can also occur more than once; occurrence and source_index preserve every entry. An adapter must select that occurrence explicitly instead of overwriting a dictionary entry.
3. Select a zero-based animation frame and a direction. The ordered directions are south, north, east, west, southeast, southwest, northeast, northwest, with BYOND direction constants also stored. Cells are ordered by animation frame, then direction.
4. Load the page identified by the cell's page value. Its rect is [x, y, width, height], measured from the top-left in integer pixels. The source_rect and source_cell values identify the original sheet location.
5. Draw the rectangle at native size or an integer scale with nearest-neighbor filtering and no mipmaps. The transparent one-pixel gutter is outside the rectangle. Frames retain unpremultiplied alpha and even the RGB values beneath fully transparent pixels.

The direction/frame ordering and decisecond timing are checked against [OpenDream's DMI parser](https://github.com/OpenDreamProject/OpenDream/blob/master/OpenDreamShared/Resources/DMIParser.cs). Every state retains dirs, frames, original delays, loop, rewind, movement, hotspots and its ordered raw metadata. The full Description text is retained as well. Delays use deciseconds; multiply by 100 for milliseconds. Missing DMI delays default to one decisecond. Raw loop values remain available for the target renderer rather than being reduced to an ambiguous boolean.

For four existing files with longer delay lists than their frame counts, delay_deciseconds retains the full list and playback_delay_deciseconds contains the first frames entries, matching the current parser's frame lookup. This is explicitly warned about. Short, nonpositive or nonfinite delay lists are rejected. GIF metadata has a separate gif object because its repeat count has different semantics.

The manifest records the raw source SHA-256, each atlas PNG hash, every cell's RGBA hash and full-sheet RGBA hash. It includes included-source hashes and copied notice hashes. It uses relative paths and no build timestamps, so identical inputs produce identical output bytes in the same tool environment.

## Existing source irregularities retained

| Finding | Treatment |
| --- | --- |
| Empty Code/Building/Stair.dmi and Icons/Funny Icons.dmi | Quarantined records with hashes/reasons. Neither is referenced by included source. |
| 20 repeated state occurrences beyond the first matching name/movement pair | All preserved under distinct IDs; consumer must choose explicitly. |
| Normal and movement versions sharing a state name | Kept separately; these are valid variants, not duplicate errors. |
| Four overlong delay lists | Original lists retained; explicit playback list and warning. |
| Painted cells after declared states in seven sheets | Retained in extra_cells, including source positions and visibility. |
| Seven source path case mismatches | Resolved to canonical file names and reported, avoiding case-sensitive export failures. |
| One GIF stored with a DMI extension | Decoded into exact RGBA frames with original GIF timing/repeat metadata. |
| Three dynamically generated PNG names in code | Informational records; they are runtime outputs, not source files. |

Malformed headers, insufficient sheet cells, unknown DMI versions, invalid directions/frame counts and corrupt PNGs are rejected and reported. Unknown metadata fields are retained with warnings. Legacy binary DMI and animated PNG input are explicitly unsupported by this exporter; the repository's older standalone/tools/legacy_dmi.py remains a separate legacy decoder. No current remastered source asset needs it.

## Verification completed

- [x] Ten focused checks cover odd cell sizes, eight directions, animation timing, rewind/loop/movement, cursor hotspots, transparent/semitransparent pixels, duplicate states, undeclared painted cells, nested source resolution, case mismatches, malformed assets, GIF frames, output safety and corruption detection.
- [x] Boundary fixture fills one page exactly; one additional frame correctly creates a second page without an empty trailing page.
- [x] All 161 PNG source sheets reconstructed from their saved atlas rectangles and compared byte-for-byte as RGBA, including unused cells and transparent pixel colors.
- [x] The GIF's frame compared against its original decoded frame.
- [x] All 9,311 stored cells checked across three saved pages.
- [x] Full export repeated; every output file hash matched.
- [x] Original sprite file hashes unchanged after export and tests.

## First consumer: original border-control glyphs

[export_border_icons.py](/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/tools/export_border_icons.py) reads the [45-control catalog](/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/game/Interface/border-controls.json), resolves each source/state with movement 0 and occurrence 0, and extracts SOUTH frame 0 from the atlas. It emits 45 original control glyphs plus Sun/Moon variants into game/Interface/border-icons. Each of the 47 outputs is a native 32 × 32 RGBA PNG; no artwork is redrawn or resized.

    python3 standalone/remastered/tools/export_border_icons.py
    python3 standalone/remastered/tools/check_border_icons.py

The [provenance report](/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/assets/border-icons-provenance.json) records catalog/manifest/source/output hashes, source and atlas rectangles, native dimensions and browser resource names. Every saved PNG is compared byte-for-byte with an independently located crop from the original DMI. Missing or ambiguous states, stale original hashes and incorrect atlas crops stop the export before replacing existing output. Browser resource names follow remaster-border-ID.png, including remaster-border-daynight-sun.png and remaster-border-daynight-moon.png.

Five [focused checks](/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/tests/border-icons-checks.json) cover exact pixels/deterministic output, ambiguity, unsafe IDs, stale sources, independently detected crop mismatches and exclusion of generated PNGs from future source-atlas builds. Regenerate the atlas before this consumer if original sprites or atlas metadata change. The consumer itself only validates the original sprite inputs it uses; unrelated gameplay-source hash changes do not affect glyph pixels.

## Integration checklist

- [x] Resolve unambiguous source/name/movement/occurrence tuples for the 45 original border controls and two day/night variants.
- [x] Verify conservative flat 32 × 32 SOUTH portraits from original hair/equipment; 455 pixel, 25 roster-cache and 65 native checks. Unsupported appearance falls back to the base portrait; broader composition stays open.
- [ ] Add a small consumer adapter that loads manifest entries, caches pages and uses nearest-neighbor sampling.
- [x] Check idle/walking variant selection and cardinal/diagonal fallback against original Deer/Sword/Human/Fire/Water cells through the real shared parser and client methods; generated constructor/Insert output is compared independently with BYOND 516.1655.
- [ ] Complete finite-loop counts, broader animation phase/timing, and remaining icon-operation parity beyond the verified rewind scope.

The installed October 17 engine changes address the previous same-name idle/walking collapse without changing the exporter or original art. See [movement implementation and limits](/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/replica/engine/MOVEMENT_ANIMATION.md) and the retained [81-check staged evidence](/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/replica/reports/dmi-variants-staged-checks.json). Raw duplicate occurrences remain in the manifest. The [follow-up BYOND audit](/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/replica/reports/dmi-edge-audit.json) verifies that first-wins lookup matches BYOND for all six same-name/same-movement groups (20 extra occurrences), including the Demon injury state. It also reproduced the reachable Retribution tapestry's missing reverse playback and generated rewind metadata. The installed [scoped rewind implementation](/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/replica/engine/DMI_REWIND_PLAN.md) preserves that metadata and follows measured BYOND reverse timing, with explicit phase and finite-loop limitations. Ordinary animated idle art, including the sword's normal state, continues animating within the recorded tests. Runtime installation and native-client evidence are separate from atlas reconstruction validation.
- [ ] Extend portraits beyond supported flat hair/equipment layers to pixel offsets, fractional alpha, tint, transforms and nested appearances; those rules live in gameplay source and cannot be inferred from DMI alone.
- [ ] Confirm page memory and texture sampling on the intended mobile renderer.
- [x] Build the atlas and export the original border glyphs before game compilation in `tools/build_app.py`; package the trusted control catalog and all 47 PNGs with the game.
- [ ] If art changes, regenerate assets and rerun the full check before packaging.

This pipeline prepares original art for reuse. It does not by itself replace the OpenDream renderer or certify that a future Godot/mobile presentation matches the original game's composed appearance.


## October 17 renderer evidence and remaining limits

For the current accepted package and pending acceptance, see the [morning handoff](/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/planning/MORNING_2026-10-17.md) and [overnight installation ledger](/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/planning/OVERNIGHT_2026-10-17.md). The evidence below describes specific shipped changes, rather than assigning this document a current package number.

Verified changes include movement-only playback, same-name normal/movement variants, rewind timing within its recorded scope, direction expansion, explicit-frame and absent-state icon constructors, and Blend frame/timing expansion. The atlas/exporter remains unchanged. All 165 original bitmap/DMI files tracked in the initial overnight source snapshot still match their hashes; this includes the separate Tomb bitmap, whereas the pipeline's 164-input inventory has a different scope.

Generated-image verification compares actual BYOND outputs. The installed frame-expansion increment passes 664 focused assertions and 153 native renderer assertions, covering 84 cells across seven original MakeBody variants and 330 client samples. Exact-name/movement Blend source selection passes 865 focused assertions and 64 native assertions, including eight complete Deer/Human body cycles. These checks establish the recorded composition/playback cases, not whole-game pixel parity. Absent-name Blend fallback, Insert-after-tint operation history, broader pixel arithmetic/OR/partial-alpha/offset behavior, finite-loop counts and broader animation phase parity remain incomplete. The fixed absent-state icon constructor is distinct from the remaining absent-name Blend boundary.

Unit portraits compose conservative flat 32 × 32 SOUTH hair/equipment with binary alpha, stable effective layers and a tested per-unit/content cache. Unsupported fractional alpha, tint, offsets, transforms and nested appearances fall back to the original base portrait. A 300-unit roster sends no repeated resources over five stable refreshes; this does not establish an unlimited session resource bound. The retained ninth-package Elf HUD panels show the composed portrait. Physical mobile texture sampling remains unverified.

Installed shared runtime `69b727e3` also preserves non-mob-before-mob order for ordinary contents insertion, with stable arrival order within each group. Its 531 core/lifecycle and 18 actual Human/Orc inventory/death comparisons match the BYOND oracle; existing sprite output comparisons remain stable. The expanded direct-list probes retain 93 differences in turf `-=`, `contents.Insert`, multi-element `Cut`/turf assignment and movable `Cut`. Four individual fields become newly different downstream of already failing operations: two surviving-object lookups after the turf-assignment exception and two `Find` indices after unsupported `Insert`. These method implementations remain outside the insertion fix; general contents parity is not established. The full generated source patch and builder match the installed DLL. See the [preserved audit](/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/replica/reference/contents-order/ninth-candidate/stage/release/AUDIT.md) and [full generated patch verification](/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/replica/reference/contents-order/ninth-candidate/full-generated-patch/report.json). No original bitmap art or atlas format changed.
