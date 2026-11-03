# Reusable race animation work

Run `python3 standalone/goa-races/character-retarget/inventory.py` from the repository root.
Open `index.html` to compare the source appearances and open existing animation rigs.
The command reads source art and writes only this inventory folder. It does not generate art.

## Established baselines

- Male Elf: GOA Reusable Animation Rig v1.
- Male Human: GOA Retarget Review - Human Male. README-CLAUDE.md records user approval;
  its older fit-report.json predates that approval. Preserve this package's renderer and local repairs.
- Male Orc: GOA Retarget Review - Orc Male. Existing cutouts and renderer, still awaiting visual review.
- These approval records do not claim all clips, exports, female bodies or hybrids are complete.

## Next work

1. Review the existing Orc beside Human and Elf before rebuilding any Orc assets.
2. Prepare female Elf and small Goblin profiles to validate the shared format across different proportions.
3. Extract remaining bodies from their own original sheets and registered zones. Available staged male
   inputs are recorded as candidates, not validated registrations. Never borrow another race's joint rows.
4. Compare each hybrid's body parts and joints with its own parent. Keep its actual artwork. Save a parent
   link plus only the necessary profile/attachment overrides when compatibility is established.
5. Batch export reviewed profiles; rerun only entries whose input/profile/renderer hashes changed.

The existing generic zone cutter adds synthetic fillers. Adapt source-preserving extraction before
bulk builds. Hidden surfaces may come from another frame of the same facing; report unavailable surfaces.
Do not automatically rerun the Orc builder: its documented behavior replaces its existing review folder.

## Keeping chat context small

Read this file and the inventory summary first. Open only the active character's profile and review notes.
The inventory saves source hashes, baseline asset/renderer hashes, and candidate inputs. It does not yet
implement incremental animation builds or certify inheritance. Silhouette differences include heads,
hair and markings; they do not automatically require another skeleton.
