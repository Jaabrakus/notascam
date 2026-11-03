# AI limb redraws

These are actual built-in `image_gen` redraws, separate from the older Python pixel-cut assets.

`approved-style-reference.png` is the combined Dwarf sheet the user selected as the desired look: original chunky character, red pixel wounds and small detached matching sprite pieces. Its appearance is approved; individual injury states still require verification.

`raw/` holds native generated PNGs, exact prompts and provenance JSON. Do not treat a requested state name in a prompt as proof that the generated frame depicts it. Check limb presence, anatomical laterality and all four views before marking a sheet ready.

The intended sets per base race are three arm-loss rows, three leg-loss rows and four detached-piece rows. All columns use South, North, East, West. Skeletons use bone ends; Gargoyles use stone breaks without blood. Preserve approved race colors and features.

Run `python3 standalone/goa-races/limbs/ai-redraws/build_review.py` to refresh `Dungeon Master Sample/AI Limb Redraws.html` and the manifest. This only indexes files and reads image metadata; it does not redraw sprites.

These source drafts are not yet registered 64×64 animation frames or replacements for the live game's assets. Check pose alignment, missing-limb combinations and animation continuity before integration. Existing in-game limb physics is reused; no new flight demo is needed.

## Rejected reuse batch

The user rejected `hybrid-reuse/` and the palette/head-splicing method. Those outputs are not finished assets. The builder has been retired. Current targeted repairs are direct native AI edits of Blond Ashen Elf and Orc Werewolf in `direct-repairs/`. Do not use the rejected batch in the game or reviews.
