# Workshop handoff coverage

The relevant implementation is the included `game/Code/Items/CraftingStations.dm`; the similarly named older files under `Code/Mob/Workshop/` are not the running implementation. This matrix concerns safe menu cancellation, actor identity after yielding prompts, and preserving Easy Orders. It does not certify every recipe or original-game parity.

| Workshop family | Accepted twelfth source and package | Recorded focused acceptance | Remaining scope |
| --- | --- | --- | --- |
| Carpentry / Paper | Commit-only handoff | Existing59 checks pass combined | Full original recipe matrix remains broader than focused checks |
| Masonry | Commit-only handoff | Existing104 checks pass combined | Full original recipe matrix |
| Smelter | Commit-only handoff | Existing84 checks pass combined | Broader race/equipment combinations |
| Ordinary campfire / Kitchen | Commit-only handoff |230 main +20 group +79 native checks | Physical input and full recipe parity |
| Good / Evil Altar | Commit-only handoff |374 main +34 edge +110 native checks | Physical input and all world contexts |
| Forge | Commit-only handoff |904 headless +134 native observations (same-run corrected quiver assertion) | Full recipe/native matrix remains broader than focused effects checks |
| Potion station | Commit-only handoff |758 headless +187 native; included in accepted tenth | Original six implemented recipes tested; seventh offered no-op retained |
| Poison station | Commit-only handoff |448 headless +210 native checks | Broader world/race/material contexts |
| Gem cutter | Commit-only handoff |774 headless +151 native checks | No native ring-success or full recipe matrix claim |
| Melter | Commit-only handoff |432 main +26 group +170 native checks | Three prompt boundaries, explicit destructive confirmation, equipped/caged/body exclusions |
| Bone craft | Commit-only handoff |1391 headless +183 native; included in accepted twelfth 56-suite pass | Original station-Race and arrow quirks retained; physical input remains separate |
| Leather works | Commit-only handoff |892 headless +145 native; included in accepted twelfth 56-suite pass | Original24 recipes and Strip behavior; broader native contexts remain |

For any migration: retain original eligibility, ranges, menu options and probabilities; capture the player and actor; recheck ownership, roster membership, life, profile and station after each yielding prompt; pause interrupted work only at an actual effect. Cancel and rejected attempts retain exact task/delivery/role/production state. Do not introduce a global Selected swap while a menu can yield. Keep headless, native callback and physical input evidence distinct.

Quick-build Campfire/Carpentry uses a separate HUD callback. Its installed sixth240-check implementation retains prior tasks and roles; a running manual production-only worker continues crafting automatically. This does not migrate other build palettes.
