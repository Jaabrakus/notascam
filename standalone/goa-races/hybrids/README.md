# Updated race designs, hybrids and missing base walks

Open `index.html` or Dungeon Master Sample / GOA Races and Hybrids.html.
The gallery includes ten living race designs (including the new fair-skinned,
blond regular Elf), seven variant appearances for each, corrected flying demon
and gargoyle sheets, the approved first Vampire flying appearance, and gargoyle
eye variants.

Variant rows are Possessed1, Possessed2, Marked, Ashen, Hellblooded, Werewolf,
Zombie. Their base races keep the updated approved GOA silhouettes. The regular
Elf has blond hair, fair skin and blue eyes; Dark Elf is the existing blue-skinned,
silver-haired Night Elf asset. Game race identifiers are preserved in metadata.

All ten living base races now have walk drafts. Each of their seven hybrid
appearances also has its own three-pose, four-direction walk sheet under
`../hybrid-animations/`. Playback and exported DMI replay neutral, step A,
neutral, step B at 200 ms per pose. The gallery supplies 82 movement sheets:
ten base walks, seventy hybrid walks and two flying demon/gargoyle loops.

**Not a complete animation-state pack.** Hybrid walking drafts are included;
female bodies, sleep and armed movement are outside this pack. Missing-limb
work is handled separately. The first
attempt to redraw the full Human atlas restored missing limbs and changed the
approved design; it is explicitly rejected and excluded. The full source audit
counts 86 original sheets and 9,004 cells; `../full-states/coverage.json` tracks
that remaining scope. New Elf assets add a race absent from the source catalog.

`generation.json`, `additional-generation.json`, `walk-generation.json` and the
prompt files record native built-in image generation. Full-resolution generated
alpha is preserved under `sheets/` and `walks/`. No generated standing frame is
repeated and labeled as a completed walk cycle.

`build_gallery.py` creates the standalone gallery. `verify_gallery.py` exercises
actual direction/frame playback, rejects empty or identical movement frames,
exports 64-pixel PNGs and DMI movement files, and reports measurable foot-baseline
drift. These checks do not establish artistic gait quality, identity consistency
or production readiness; inspect the loops before game integration.

Walk registration measures each complete source silhouette and packs it at a common foot anchor (y62), using one scale per race. The source AI sheets have uneven spacing; equal-grid cropping is deliberately avoided for these walks. Source PNGs remain intact. See walk-registration.json and playback-verification.json.

Hybrid design rows also use measured sprite rectangles from variant-registration.json. This fixes neighboring-row feet leaking above heads and truncated legs from equal-height slicing. The same registration is applied in the viewer and exported atlases; no redraw or limb removal is involved.
