# Full female set in progress

The user explicitly rejected stopping after three base females. Current scope is the full existing female roster: 10 races × (base + 7 hybrid appearances) = 80 appearances. No individual detached pieces are requested. Existing female designs come from `female-animations`; that source directory is read-only for this work.

Use direct built-in image-generation edits of each exact female reference. The user rejected the previous palette/head-splicing/body-warp reuse batch. Mechanical whole-frame ordering, nearest-neighbor packing and isolated-pixel cleanup are permitted; do not recreate injured bodies from cuts of intact art.

`prepare_all.py` stages frozen references and `normal64.png` in `all/<race>/<appearance>`. All 80 references are ready. `all-catalog.json` describes paths. Category status strings are snapshots; actual PNG existence is authoritative.

Two native sheets per appearance: arms (NoLeftArm, NoRightArm, NoArms) and legs (NoLeftLeg, NoRightLeg, NoLegs), each 3 rows × 4 direction columns South/North/East/West. Final PNG/DMI: 7 states including Normal, 64×64, foot baseline 62. Existing first-set Human/Elf/Orc base native sheets are reused from this directory's top level.

`pack_all.py` builds `all-coverage.json`, `all-packed.json` and `Dungeon Master Sample/All Female Limb Sheets.html`. It detects ambiguous single-limb side assignments and records flags. Do not claim all forms complete while sheets are missing or pose defects are unresolved. Walking injury frames are not generated; existing normal female walks are a separate asset set.

Native generation is checkpointed by writing every PNG, exact prompt and provenance JSON immediately into its appearance folder. Long orchestration checks `STOP_ALL` between appearances; current image calls finish and save before stopping. A fresh run must skip files already present. Do not terminate running calls merely to restart scheduling, because that can lose output associations. Tool-store writes inside a still-running exec module are not available to other exec calls until it completes; use filesystem checkpoints.

The first Human-family batch (14 new sheets) completed. The dark-skinned Human family is drawn. Dwarf variants are underway. A checkpoint stop was requested to resume the remaining work with a larger independent call pool, without discarding in-flight images.

Four back-facing single-pose corrections are described in `first-pose-repairs.json`. Their complete native corrective images were inspected: intended screen-side limb absent, opposite limb present. Override application requires `visualReview: accepted` in the correction's JSON. The accepted-marking command was issued. `pack_all.py` preserves these reviewed poses and suppresses only their resolved flags.

After the remaining generation: retry failed sheets; inspect and directly redraw flagged single poses; pack and verify all 80 appearances / 160 native sheets / 2,240 standing frames; publish the complete preview and portable export. Include source prompts/provenance. Never present the rejected male `hybrid-reuse` batch or mere queued references as finished art.

## Latest full-roster checkpoint

All 80 appearances now have native artwork and all 160 category PNGs exist. 80 injury atlases pack successfully, with no packing errors. Main generation cell 179 completed 31 combined six-row atlases with zero errors; its final image buffer exceeded the tool IPC frame limit. Do NOT re-poll that image buffer: artwork and metadata are saved, and combined-generation-results.json confirms completion. Earlier main cell 134 completed 26 appearances/52 native sheets and is closed.

The final 32 small/creature appearances use combined-6rows-v1.png with complete-row extraction via split_combined.py. All 32 have an extra direct native both-arms-missing pass in no-arms-repairs (eight 4x4 atlases), split via split_no_arms.py into 128 complete-pose overrides. All 128 were visually checked for absent arms, intact legs/feet and genuine attached tails; accepted overrides are applied before single-side classification. Two Marked forms (Goblin and Lizard) acquired extra leg decorations: cell 192 is correcting only those decorations in a 2x4 atlas. Once finished, inspect, split with split_no_arms.py, and accept all eight corrected complete-pose overrides.

The original base female Orc first-set artwork contained a tail but the current approved normal reference does not. Cell 182 generated current arms-v2-no-tail.png and legs-v2-no-tail.png in all/Orc/base, both inspected. The catalog now selects these instead of old first-set raw files. prepare_all.py now preserves selected category revisions. The stalled apply_patch cell 186 was terminated before applying; the equivalent edits and catalog selection succeeded via exec cell 188.

The four initial corrections, five pose-repair-group corrections and four review-02 groups are accepted. Current review-03 collects 38 remaining ambiguous or incorrect single-side poses in 13 groups. The four comparison images were inspected. Cell 197 is actively generating all 13 direct corrective atlases with four workers; every result saves immediately as review-03-group-NN-corrected.png/json/prompt.txt. Inspect each output, split complete poses with split_pose_groups.py, mark individual overrides visualReview=accepted, then pack again. Corrected overrides must be applied AFTER automatic original row ordering; row2 both-arms corrections are applied BEFORE ordering to give it an accurate baseline.

Current pack: 80/80 packed, 28 appearances flagged for single-side review; no empty/missing category files. Do not finalize until review-03 is applied and remaining genuine defects repaired. Then verify_all.py --require-complete, browser-check all 80 preview options and export_all.py. Normal female movement assets already cover all80 with playback verification; those source files remain read-only. Injured walk animations, attacks, sleep and live integration are NOT completed.
