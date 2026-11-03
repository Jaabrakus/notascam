# Smelter prompt and work handoff audit

The private candidate changes only the Smelters block in
`game/Code/Items/CraftingStations.dm` and its single-tap handoff exemption in
`game/Code/Remastered/QoL.dm`. It starts from CraftingStations SHA256
`023f44aa7d71532e095a8397d3f5642fd18bddd7cefb66cfbca49e7a934c8fdb`,
which includes the accepted Carpentry Paper eligibility recheck.
Canonical gameplay promotion completed in the fourth source integration. The combined run passes84 Smelter assertions; the fourth app packaged Human startup/save/reload lifecycle passed at03:24 Eastern.

## Reproduced failures

The original failure branch deletes the consumed ore and then reads `S.name`.
The retained `tests/smelter-before-caught-checks.json` records the resulting
`Cannot get field "name" from <deleted>` exception and incomplete two-item batch.
It also reproduces single-tap Cancel, no-ore, stone-only, Spider and Wagon choices
pausing current work; direct successful smelting failing to hand off automatic
work; and ownership/race changes during the prompt still consuming the original
actor's ore. There are 18 failing outcomes across real Human/Orc constructors.
Original Iron conversion and workshop-deletion rejection pass before the change.

`smelter-before-checks.json` is preserved as the initial diagnostic. Its exception
reporter itself expected an exception datum although this runtime throws a string;
the corrected before report catches and records the original exception directly.

## Candidate behavior

Opening the menu, cancelling it, having only stone/no ore, or failing original
Spider/Wagon restrictions leaves queue, role and defense state unchanged. A real
material attempt or an in-range Destroy action calls the shared manual handoff:
it pauses automatic work, keeps active and pending task identities and role/
production configuration, and releases any current defense response. Both failed
and successful material attempts commit that handoff.

The menu keeps its originally selected actors. Changing or clearing selection
while it is open does not send the old choice to a newly selected unit. The
initiating Player, owned roster membership, living state, Race/SubRace/IsMist
profile, Wagon restriction, actor and workshop must remain valid after the
prompt. Deleted controllers or actors and ownership changes cannot commit a
stale choice. Like other migrated workshops, Smelter does not grant crafting on
foreign FreeSelect units. Material enumeration remains the original current
inventory batch, so items removed while the prompt is open are not processed.

The failure message snapshots the original material name before item deletion.
The five original mappings, probability multipliers, pre-roll skill gains,
DropItem/PickUpItem effects and weight accounting remain unchanged:

| Material | Product | Skill gain per attempted item | Chance multiplier |
| --- | --- | --- | --- |
| Iron | Iron ingot | 0.25 | 5 |
| Silver | Silver ingot | 0.5 | 4 |
| Gold | Gold ingot | 0.75 | 3 |
| Adamantium | Adamantium ingot | 10 | 1 |
| Sand | Empty bottle | 0.25 | 5 |

Stone is excluded as before. Smelting has no proximity gate in the original
handler, and this candidate preserves that behavior explicitly. Destroy still
requires the actor within one tile and calls the same original station-removal
procedure. No balancing or other workshop family is changed.

## Verification

`tests/smelter-candidate-final-checks.json` passes **84/84** with no errors. It
covers original Human/Orc units; all five materials in successful and failed
batches; exact consumed/produced inventory, carried weight and skill gains;
unrelated wood/stone cargo; preserved FIFO/role/production identities; prompt
lifetime/profile/ownership changes; selection/deselection; multiple captured
actors; material removal; workshop deletion; range behavior; and actual defense
state during cancel, empty and committed actions.

Failure cases use deliberately low skill data to force the original probability
branch; success cases use guaranteed original skill thresholds. Production
probability code is not replaced. Only modal reply delivery is scripted. The tap
cases execute the handoff plus original DblClick sequence verified against the
source branch; they do not claim native mouse or WebKit input coverage.

The isolated run copies runtime and compiler artifacts: runtime
`3879e6f7ad058d41d6fd8e65082f188829696489136515b1aadbf5b0bef590db` and
updated grid-distance standard `56851ae1…`. The full hashes and fixture stability
are in the report. Normal app, saves and OS input are untouched.

The Carpentry regression harness now recognizes its own explicit deferred
handoff clause independently of other workshop exclusions on the same line.
This is a test-only parsing correction. Its focused regression passes **59/59**, including the accepted Paper gate, in
`tests/smelter-carpentry-regression-checks.json`; no runtime errors.
