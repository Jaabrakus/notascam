# Current sprite locations

The organized sample copy is **Dungeon Master Sample/Sprites/**. Its README and manifest identify every asset and working source.

Working race/variant sheets: hybrids/packed/ (male) and female-animations/assets/ (female). Human corrections are published to those locations. Hybrid movement sources remain in hybrid-animations/assets/. Existing actions are in held-equipment-demo/combat/; universal clips and previews in universal-animation/. Equipment is in armory/. Limb/injury work stays in limbs/ and is managed separately. Armor and gear design sources retain their existing folders.

Use the current sheets and sample exports, not numbered human-hand-corrections or human-remake experiments. Those retain source artwork and history.

Human sheets are now rebuilt from full redraw frames with `rebuild_human_sheets.py --publish`. The direct sample is `Dungeon Master Sample/Human Sprites/index.html`; this build supersedes the earlier patch-only candidate PNGs. The publish check compares all 48 inserted frames and each sample/archive copy with the current canonical sheets.
